# Hyperliquid Bridge2 — Topics, Selectors, Addresses (Arbitrum One only)

**Status:** verified against live RPC on all seven target chains and the canonical `hyperliquid-dex/contracts` repo (`Bridge2.sol` + `Signature.sol`, master branch) on 2026-06-09.
**Scope:** the single `Bridge2` contract — Hyperliquid's USDC deposit/withdrawal bridge between Arbitrum One and the Hyperliquid L1 (HyperCore). Topics and selectors are **chain-agnostic** (keccak256 of the canonical signature); the address is **Arbitrum-only**. `Bridge2` is **not deployed on any of the other six target chains** (`eth_getCode` = `0x` on Ethereum, Base, BNB, Avalanche, Optimism, Polygon).

`Bridge2` is a **single, immutable, non-proxy** contract at `0x2Df1c51E09aECF9cacB7bc98cB1742757f163dF7` on Arbitrum One (chain 42161). It is **not upgradeable** (all EIP-1967 impl/admin/beacon slots read `0x0`), **not Ownable**, and has **no admin EOA** — every privileged action is gated by **validator multisig signatures** (a 2/3-of-power quorum from a hot or cold validator set). There is no factory, no per-token vault, no router; the bridge holds native USDC directly and the Hyperliquid L1 validators are the relayers.

The single most important fact for an indexer: **a normal deposit emits NO event from `Bridge2`.** Users simply `transfer()` native USDC to the bridge address; the L1 validators watch the **USDC `Transfer(...→bridge)`** log and credit HyperCore off-chain. The `Deposit(address,uint64)` event is *defined* in the ABI but **never emitted** in the deployed code — it is a vestigial/forward-compat definition. The only deposit *function* is `batchedDepositWithPermit` (EIP-2612 permit deposits on behalf of users), and even that emits `FailedPermitDeposit` on failure, not `Deposit` on success. To track deposits you MUST index the USDC token's `Transfer` event filtered on `to = bridge`, **not** any `Bridge2` event.

Withdrawals are the visible flow: `RequestedWithdrawal` (validator-signed, enters a dispute period) → `FinalizedWithdrawal` (paid out after the dispute period). These two topics dominate the contract's live log volume.

> **Lifecycle note:** Hyperliquid has announced the Arbitrum bridge will be **deprecated** in favor of natively-minted USDC on HyperEVM/HyperCore. As of 2026-06-09 the contract is live and active (epoch 7, 4 validators, not paused), but expect this bridge to wind down. Keep indexing the address until withdrawal volume goes to zero.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Bridge2

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xcc10abf54af5c0718b10b0156dfe1e369ce3eee72423e9e86936a0082e9c5d1b` | `RequestedWithdrawal(address,address,uint64,uint64,bytes32,uint64)` | Validator-signed withdrawal queued; enters dispute period. **Verified live** (dominant topic). |
| `0xe5c7fe3a4ffca1590f26d74c8ba8b0db69557f7f4607a2a43f82e93041611978` | `FinalizedWithdrawal(address,address,uint64,uint64,bytes32)` | USDC paid out after dispute period. **Verified live** (dominant topic). |
| `0x686cb4bac974cd11b0f8a75fc7c7764ed12cc46faaec53110f807aa802a7acb4` | `FailedWithdrawal(bytes32,uint32)` | A queued withdrawal could not be requested/finalized (carries an `errorCode`). **Verified live.** |
| `0xa2dc875d1f90a167d873c30143e7631eb311ea851e74c8c4e9b92c80efeba489` | `FailedPermitDeposit(address,uint64,uint32)` | A permit deposit in `batchedDepositWithPermit` failed. **Verified live.** |
| `0x0ee94a97c7c69ce2eb8cfb09bacc78d63a73b5e0fbed0d13a079190ff876ae3a` | `Deposit(address,uint64)` | **Defined but NEVER emitted** by the deployed contract — see §5.1. Do not rely on it. |
| `0x1d1674a854ef85d43fe928545420db98386c6a01fa1c7bc45efe559579416405` | `InvalidatedWithdrawal((address,address,uint64,uint64,uint64,uint64,bytes32))` | Cold-validator-signed cancellation of a requested withdrawal during the dispute window. Param is the full `Withdrawal` struct. |
| `0x420bbe99bd2c52ec500d33614359525f3ef7bb3358c0e07d1312db0941cbf2f4` | `RequestedValidatorSetUpdate(uint64,bytes32,bytes32,uint64)` | New validator set proposed (epoch, hot-set hash, cold-set hash, time); enters dispute period. |
| `0x87da17ff65d815d1e1c369cb3bbda9a11af181b92dc52681a2779419781c6270` | `FinalizedValidatorSetUpdate(uint64,bytes32,bytes32)` | Validator set rotation applied. **Watch this — it changes the signers that authorize every privileged action.** |
| `0x26690dc5c5a9d2aa7ac3efa2b7c515652e4621a3e075d267bcac51c16fb97532` | `ModifiedLocker(address,bool)` | Locker added/removed (lockers can trigger an emergency pause). |
| `0x2526bb92d75e00cfad8c7c16cb75f3e1073c854339e49b16baaad3067c2ed65a` | `ModifiedFinalizer(address,bool)` | Finalizer added/removed (finalizers may call the finalize/request paths). |
| `0x04edaf680108675f58d2ea70e9e7886c39ed38b66439622f8362d36595fe8169` | `ChangedDisputePeriodSeconds(uint64)` | Dispute period changed (cold-validator-signed). |
| `0x0ef2da393c3832a8f08ce447e14948d21e84f864facf7327137387bd0596a563` | `ChangedBlockDurationMillis(uint64)` | Block-duration param changed. |
| `0x2dbe453726b24b2cee427a7d6e2dcc9f353f16bee104f3d21480157a0ee409f7` | `ChangedLockerThreshold(uint64)` | Number of locker votes needed for emergency lock changed. |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address)` | OZ `Pausable` — **emergency lock engaged** (lockers reached threshold). High-severity alert. |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address)` | OZ `Pausable` — bridge unlocked (via `emergencyUnlock`, cold-validator-signed). |

There are **no topic0 collisions** within `Bridge2` and (since it is a single isolated contract) none to disambiguate across emitters — but `Deposit`, `Paused`, `Unpaused` are generic signatures shared with many other contracts on Arbitrum, so always filter `(address = bridge, topic0)`.

### 1.2 USDC (the real deposit signal)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address,address,uint256)` | Emitted by the **USDC** contract `0xaf88…5831`, not by `Bridge2`. **`Transfer(_, bridge, amount)` IS the deposit.** This is the canonical ERC-20 Transfer topic. |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

All selectors below were confirmed present in the deployed runtime bytecode (PUSH4 dispatch) at `0x2Df1c51E…3dF7` on Arbitrum.

### 2.1 Bridge2 — state-changing

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb30b5bce` | `batchedDepositWithPermit((address,uint64,uint64,(uint256,uint256,uint8))[])` | The **only** deposit function: EIP-2612 permit deposits. Each `DepositWithPermit` = `(user, usd, deadline, Signature)`. Emits `FailedPermitDeposit` on a per-item failure; **does not emit `Deposit` on success**. |
| `0x1f12171f` | `batchedRequestWithdrawals((address,address,uint64,uint64,(uint256,uint256,uint8)[])[],(uint64,address[],uint64[]))` | Validator-signed batch of withdrawals → `RequestedWithdrawal`. 2nd arg is the active **hot** `ValidatorSet`. |
| `0xc5bdf3ca` | `batchedFinalizeWithdrawals(bytes32[])` | Finalize queued withdrawals after dispute period → `FinalizedWithdrawal`. Keyed by `message` hash. |
| `0xe3e6c441` | `updateValidatorSet((uint64,address[],address[],uint64[]),(uint64,address[],uint64[]),(uint256,uint256,uint8)[])` | Propose a new validator set (hot+cold addresses+powers) → `RequestedValidatorSetUpdate`. |
| `0x058731e5` | `finalizeValidatorSetUpdate()` | Apply the pending validator set after dispute period → `FinalizedValidatorSetUpdate`. |
| `0x9770e2c8` | `emergencyUnlock((uint64,address[],address[],uint64[]),(uint64,address[],uint64[]),(uint256,uint256,uint8)[],uint64)` | **`whenPaused`** — cold-validator-signed unlock (also rotates the validator set). High-severity. |
| `0x4878ee53` | `voteEmergencyLock()` | A locker votes to pause the bridge. When votes ≥ `lockerThreshold`, the bridge pauses → `Paused`. |
| `0xb091049c` | `unvoteEmergencyLock()` | Withdraw an emergency-lock vote (`whenNotPaused`). |
| `0x180f2e8c` | `modifyLocker(address,bool,uint64,(uint64,address[],uint64[]),(uint256,uint256,uint8)[])` | Add/remove a locker (validator-signed) → `ModifiedLocker`. |
| `0xe73ea41e` | `modifyFinalizer(address,bool,uint64,(uint64,address[],uint64[]),(uint256,uint256,uint8)[])` | Add/remove a finalizer (validator-signed) → `ModifiedFinalizer`. |
| `0x0fb61a2e` | `invalidateWithdrawals(bytes32[],uint64,(uint64,address[],uint64[]),(uint256,uint256,uint8)[])` | **Cold**-validator-signed cancel of pending withdrawals → `InvalidatedWithdrawal`. Anti-theft control. |
| `0x91ed1344` | `changeDisputePeriodSeconds(uint64,uint64,(uint64,address[],uint64[]),(uint256,uint256,uint8)[])` | Cold-validator-signed → `ChangedDisputePeriodSeconds`. |
| `0x4aad6210` | `changeBlockDurationMillis(uint64,uint64,(uint64,address[],uint64[]),(uint256,uint256,uint8)[])` | Cold-validator-signed → `ChangedBlockDurationMillis`. |
| `0xfc3f7ad3` | `changeLockerThreshold(uint64,uint64,(uint64,address[],uint64[]),(uint256,uint256,uint8)[])` | Cold-validator-signed → `ChangedLockerThreshold`. |

Tuple shapes used above (canonical, names stripped):
- `Signature` = `(uint256 r, uint256 s, uint8 v)` → `(uint256,uint256,uint8)`
- `ValidatorSet` = `(uint64 epoch, address[] validators, uint64[] powers)` → `(uint64,address[],uint64[])`
- `ValidatorSetUpdateRequest` = `(uint64,address[] hot,address[] cold,uint64[] powers)` → `(uint64,address[],address[],uint64[])`
- `WithdrawalRequest` = `(address user,address destination,uint64 usd,uint64 nonce,Signature[])` → `(address,address,uint64,uint64,(uint256,uint256,uint8)[])`
- `DepositWithPermit` = `(address user,uint64 usd,uint64 deadline,Signature)` → `(address,uint64,uint64,(uint256,uint256,uint8))`
- `Withdrawal` (event/getter) = `(address,address,uint64,uint64,uint64,uint64,bytes32)`

### 2.2 Bridge2 — views & public getters (all confirmed in bytecode)

| Selector | Signature | Live value (Arbitrum, 2026-06-09) |
|----------|-----------|-----------------------------------|
| `0x11eac855` | `usdcToken()` | `0xaf88d065e77c8cc2239327c5edb3a432268e5831` (native Arbitrum USDC) |
| `0x900cf0cf` | `epoch()` | `7` |
| `0xf8156a6e` | `totalValidatorPower()` | `4` |
| `0x0833c91a` | `nValidators()` | `4` |
| `0x0756183b` | `disputePeriodSeconds()` | `200` (`0xc8`) |
| `0x9d5bc9e1` | `blockDurationMillis()` | `350` (`0x15e`) |
| `0x05355e23` | `lockerThreshold()` | `2` |
| `0xb0801e54` | `hotValidatorSetHash()` | `0x1503ca1a4eac24ce351d93ef962f13cb745a9d08f50cef522ca8aa216e13fb7f` |
| `0x0f711438` | `coldValidatorSetHash()` | `0x55a3e95e596d9e4918403663b9e83d046fdf17cdcbdb4fe6bf5429afde0adc2d` |
| `0x5c975abb` | `paused()` | `false` (`0x0`) |
| `0xc10ee9ae` | `pendingValidatorSetUpdate()` | `PendingValidatorSetUpdate` struct getter |
| `0x53f79ef4` | `getLockersVotingLock()` | `address[]` — lockers currently voting to pause |
| `0x3a37326e` | `isVotingLock(address)` | `bool` |
| `0x5a028400` | `usedMessages(bytes32)` | `bool` — EIP-712 message replay guard |
| `0x2c8e7a21` | `lockers(address)` | `bool` |
| `0xcea75eb7` | `finalizers(address)` | `bool` |
| `0x7694c6fa` | `requestedWithdrawals(bytes32)` | `Withdrawal` struct getter (keyed by `message`) |
| `0xa14238e7` | `finalizedWithdrawals(bytes32)` | `bool` |
| `0x42082828` | `withdrawalsInvalidated(bytes32)` | `bool` |

There is **no `owner()` / `admin()` getter** — confirmed by absence in the bytecode (the contract is not Ownable).

---

## 3. Addresses — Arbitrum One (chain ID 42161)

Verified via `eth_getCode` returning non-empty bytecode (19 394 B) on `https://arbitrum-one-rpc.publicnode.com` on 2026-06-09.

| Role | Address | One-liner |
|------|---------|-----------|
| **Bridge2** | `0x2Df1c51E09aECF9cacB7bc98cB1742757f163dF7` | The deposit/withdrawal bridge. Immutable, non-proxy, validator-multisig-gated. Holds native USDC. |
| **USDC** (native) | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | Circle native USDC on Arbitrum (6 dec). `Bridge2.usdcToken()` returns exactly this. **Index its `Transfer(_, bridge, _)` for deposits.** |

**Not present on Arbitrum:** there is no governance contract, no proxy admin, no timelock, no factory, no per-token vault — the bridge is self-contained. The validator hot/cold addresses are EOAs derived off-chain (the contract stores only the *hashes* `hotValidatorSetHash` / `coldValidatorSetHash`, not the address lists).

### Other six target chains — NOT deployed

`eth_getCode` for `0x2Df1c51E…3dF7` returns `0x` (no code) on every other target chain, confirmed live on 2026-06-09:

| Chain | ID | RPC | `Bridge2` code |
|-------|----|-----|----------------|
| Ethereum | 1 | ethereum-rpc.publicnode.com | `0x` (absent) |
| Base | 8453 | base-rpc.publicnode.com | `0x` (absent) |
| BNB Smart Chain | 56 | bsc-rpc.publicnode.com | `0x` (absent) |
| Avalanche C-Chain | 43114 | avalanche-c-chain-rpc.publicnode.com | `0x` (absent) |
| Optimism | 10 | optimism-rpc.publicnode.com | `0x` (absent) |
| Polygon PoS | 137 | polygon-bor-rpc.publicnode.com | `0x` (absent) |

The address is **not** a deterministic CREATE2 vanity reused elsewhere — it was a one-off CREATE deploy on Arbitrum only.

### Counterparty chain (outside the seven)

The bridge's other endpoint is **Hyperliquid L1 / HyperCore** — a custom, non-EVM-indexable settlement layer (and **HyperEVM**, chain ID **999**, which is also outside the seven target chains). Crediting/debiting on that side happens off-chain via validator consensus, not via an EVM contract you can `eth_getLogs`. The Hyperliquid **testnet** bridge `0x08cfc1B6b2dCF36A1480b99353A354AA8AC56f89` lives on **Arbitrum Sepolia (421614)** — not a target chain, and it returns `0x` on Arbitrum One mainnet.

---

## 4. Cross-chain summary

| Chain | ID | Bridge2 | USDC (bridge underlying) |
|-------|----|---------|--------------------------|
| **Arbitrum One** | 42161 | ✓ `0x2Df1c51E…3dF7` | ✓ `0xaf88…5831` (native) |
| Ethereum | 1 | – | n/a |
| Base | 8453 | – | n/a |
| BNB Smart Chain | 56 | – | n/a |
| Avalanche C-Chain | 43114 | – | n/a |
| Optimism | 10 | – | n/a |
| Polygon PoS | 137 | – | n/a |

No vanity-address tell (the address has no recognizable pattern). Hyperliquid runs **exactly one** bridge contract, on **exactly one** chain.

---

## 5. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **Bridge2** | **Immutable — NOT a proxy** | EIP-1967 impl slot `0x360894…bbc` = `0x0`; admin slot `0xb53127…6103` = `0x0`; beacon slot `0xa3f0ad…3d50` = `0x0` (all read live on Arbitrum). 19 394 B of self-contained runtime bytecode; no `DELEGATECALL`-to-impl dispatch. | None. The contract **cannot be upgraded.** Parameters (dispute period, thresholds, validator set) are mutated in place via validator-signed calls; the *code* is fixed. |

There is **no `Upgraded(address)` event to watch** — the contract is not upgradeable. The closest analog to "the authority changed" is **`FinalizedValidatorSetUpdate`** (`0x87da17ff…6270`): when the validator set rotates, the signers who can authorize withdrawals/admin actions change. Treat that event as the upgrade-equivalent alert.

---

## 6. Detection invariants & gotchas

1. **A deposit emits NO `Bridge2` event.** Deposits are plain `usdcToken.transfer(bridge, amount)` calls; the L1 validators detect the **USDC `Transfer(_, bridge, _)`** log and credit HyperCore off-chain. To index deposits, filter the **USDC** contract (`0xaf88…5831`) for `Transfer` with `to = 0x2Df1c51E…3dF7`. **Do not** index the `Bridge2` `Deposit` topic.
2. **`Deposit(address,uint64)` is defined but never emitted** by the deployed code (confirmed: no `emit Deposit` in source, and zero such logs across hundreds of thousands of recent blocks). Its topic `0x0ee94a97…ae3a` will never appear from this contract. It is a vestigial ABI entry.
3. **`batchedDepositWithPermit` is a relayer/sponsor path, not a normal deposit.** The `usd` (uint64, 6-dec) credited goes to the `user` field inside each `DepositWithPermit`, while the actual `msg.sender` is a relayer. On *failure* it emits `FailedPermitDeposit(user, usd, errorCode)`; on success it emits **nothing** — the deposit is again just the USDC `Transfer`.
4. **Withdrawals are two-phase.** `RequestedWithdrawal` (queued, dispute period starts) ≠ money out. Funds leave only at **`FinalizedWithdrawal`** (after `disputePeriodSeconds`, live = 200 s). Both share the same `message` `bytes32` key — join request↔finalize on `message`, not on `(user,nonce)` alone. A `RequestedWithdrawal` can be killed mid-window by `InvalidatedWithdrawal` and never finalize.
5. **`message` (bytes32) is the canonical withdrawal key**, an EIP-712 hash over `(user,destination,usd,nonce)`. It is the indexed/unindexed field that links `RequestedWithdrawal` → `FinalizedWithdrawal` / `InvalidatedWithdrawal` / `FailedWithdrawal`, and the key for the `requestedWithdrawals`/`finalizedWithdrawals`/`withdrawalsInvalidated`/`usedMessages` mappings.
6. **The "user" in withdrawal events is the HyperCore-side withdrawer; `destination` is the Arbitrum recipient.** Both are in the event. `usd` is a **uint64 in USDC 6-decimal units** (not 1e18, not signed) — scale by 1e-6.
7. **No owner, no admin, no timelock.** Every privileged function (`modifyLocker`, `modifyFinalizer`, `change*`, `invalidateWithdrawals`, `updateValidatorSet`, `emergencyUnlock`) is authorized by **validator signatures** passed as calldata, verified against `hotValidatorSetHash` or `coldValidatorSetHash`. There is no EOA whose key compromise alone moves funds — but a 2/3 validator-key compromise does. **Cold**-set actions (`invalidateWithdrawals`, all `change*`, `emergencyUnlock`) are the higher-trust controls.
8. **`Paused` is the emergency-lock alert (highest severity).** Lockers call `voteEmergencyLock`; at `lockerThreshold` votes (live = 2) the bridge pauses and `batchedRequestWithdrawals`/`batchedFinalizeWithdrawals`/`batchedDepositWithPermit` all halt (`whenNotPaused`). Only `emergencyUnlock` (cold-signed, `whenPaused`) clears it → `Unpaused`. A `Paused` during normal operation is a strong incident signal.
9. **`FinalizedValidatorSetUpdate` rotates the signer set** — there is no `Upgraded` event because the contract is immutable. Watch this topic to know *who* can now sign. Note `nValidators` / `totalValidatorPower` (live = 4 / 4) and `epoch` (live = 7) move with it.
10. **`FailedWithdrawal(message, errorCode)` fires when a queued withdrawal can't proceed** (e.g. insufficient balance, already used). It is emitted multiple times in the source; treat a spike as an operational/liquidity signal, not a success.
11. **Single chain, single contract.** Anyone "monitoring Hyperliquid on Ethereum/Base/etc." is looking in the wrong place — the bridge is **Arbitrum-only**. The other endpoint (HyperCore / HyperEVM chain 999) is non-EVM-indexable here.
12. **The address is not CREATE2-deterministic.** Don't assume the same address could appear on another chain — it is a one-off Arbitrum CREATE deployment and returns `0x` everywhere else.
13. **USDC is fee-free standard ERC-20 here** (native Circle USDC, not a fee-on-transfer token), so the `Transfer` amount to the bridge equals the credited amount (modulo the 6-dec `usd` truncation the L1 applies).

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) — Bridge2 =====
TOPIC_REQUESTED_WITHDRAWAL          = '\xcc10abf54af5c0718b10b0156dfe1e369ce3eee72423e9e86936a0082e9c5d1b'
TOPIC_FINALIZED_WITHDRAWAL          = '\xe5c7fe3a4ffca1590f26d74c8ba8b0db69557f7f4607a2a43f82e93041611978'
TOPIC_FAILED_WITHDRAWAL             = '\x686cb4bac974cd11b0f8a75fc7c7764ed12cc46faaec53110f807aa802a7acb4'
TOPIC_FAILED_PERMIT_DEPOSIT         = '\xa2dc875d1f90a167d873c30143e7631eb311ea851e74c8c4e9b92c80efeba489'
TOPIC_INVALIDATED_WITHDRAWAL        = '\x1d1674a854ef85d43fe928545420db98386c6a01fa1c7bc45efe559579416405'
TOPIC_REQ_VALIDATOR_SET_UPDATE      = '\x420bbe99bd2c52ec500d33614359525f3ef7bb3358c0e07d1312db0941cbf2f4'
TOPIC_FIN_VALIDATOR_SET_UPDATE      = '\x87da17ff65d815d1e1c369cb3bbda9a11af181b92dc52681a2779419781c6270'
TOPIC_MODIFIED_LOCKER               = '\x26690dc5c5a9d2aa7ac3efa2b7c515652e4621a3e075d267bcac51c16fb97532'
TOPIC_MODIFIED_FINALIZER            = '\x2526bb92d75e00cfad8c7c16cb75f3e1073c854339e49b16baaad3067c2ed65a'
TOPIC_CHANGED_DISPUTE_PERIOD        = '\x04edaf680108675f58d2ea70e9e7886c39ed38b66439622f8362d36595fe8169'
TOPIC_CHANGED_BLOCK_DURATION        = '\x0ef2da393c3832a8f08ce447e14948d21e84f864facf7327137387bd0596a563'
TOPIC_CHANGED_LOCKER_THRESHOLD      = '\x2dbe453726b24b2cee427a7d6e2dcc9f353f16bee104f3d21480157a0ee409f7'
TOPIC_PAUSED                        = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UNPAUSED                      = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
-- Defined but NEVER emitted by the deployed contract (do not rely on it):
TOPIC_DEPOSIT_UNUSED                = '\x0ee94a97c7c69ce2eb8cfb09bacc78d63a73b5e0fbed0d13a079190ff876ae3a'
-- The REAL deposit signal (emitted by USDC, not Bridge2):
TOPIC_ERC20_TRANSFER                = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

-- ===== Selectors — Bridge2 =====
SEL_BATCHED_DEPOSIT_WITH_PERMIT     = '\xb30b5bce'
SEL_BATCHED_REQUEST_WITHDRAWALS     = '\x1f12171f'
SEL_BATCHED_FINALIZE_WITHDRAWALS    = '\xc5bdf3ca'
SEL_UPDATE_VALIDATOR_SET            = '\xe3e6c441'
SEL_FINALIZE_VALIDATOR_SET_UPDATE   = '\x058731e5'
SEL_EMERGENCY_UNLOCK                = '\x9770e2c8'
SEL_VOTE_EMERGENCY_LOCK             = '\x4878ee53'
SEL_UNVOTE_EMERGENCY_LOCK           = '\xb091049c'
SEL_MODIFY_LOCKER                   = '\x180f2e8c'
SEL_MODIFY_FINALIZER                = '\xe73ea41e'
SEL_INVALIDATE_WITHDRAWALS          = '\x0fb61a2e'
SEL_CHANGE_DISPUTE_PERIOD           = '\x91ed1344'
SEL_CHANGE_BLOCK_DURATION           = '\x4aad6210'
SEL_CHANGE_LOCKER_THRESHOLD         = '\xfc3f7ad3'
-- views / getters
SEL_USDC_TOKEN                      = '\x11eac855'
SEL_EPOCH                           = '\x900cf0cf'
SEL_TOTAL_VALIDATOR_POWER           = '\xf8156a6e'
SEL_N_VALIDATORS                    = '\x0833c91a'
SEL_DISPUTE_PERIOD_SECONDS          = '\x0756183b'
SEL_BLOCK_DURATION_MILLIS           = '\x9d5bc9e1'
SEL_LOCKER_THRESHOLD                = '\x05355e23'
SEL_HOT_VALIDATOR_SET_HASH          = '\xb0801e54'
SEL_COLD_VALIDATOR_SET_HASH         = '\x0f711438'
SEL_PAUSED                          = '\x5c975abb'
SEL_PENDING_VALIDATOR_SET_UPDATE    = '\xc10ee9ae'
SEL_GET_LOCKERS_VOTING_LOCK         = '\x53f79ef4'
SEL_IS_VOTING_LOCK                  = '\x3a37326e'
SEL_USED_MESSAGES                   = '\x5a028400'
SEL_LOCKERS                         = '\x2c8e7a21'
SEL_FINALIZERS                      = '\xcea75eb7'
SEL_REQUESTED_WITHDRAWALS           = '\x7694c6fa'
SEL_FINALIZED_WITHDRAWALS           = '\xa14238e7'
SEL_WITHDRAWALS_INVALIDATED         = '\x42082828'

-- ===== Proxy slots (all read 0x0 on Bridge2 — it is NOT a proxy) =====
EIP1967_IMPL_SLOT                   = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT                  = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'
EIP1967_BEACON_SLOT                 = '\xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50'

-- ===== Addresses — Arbitrum One (chain ID 42161) ONLY =====
ARB_BRIDGE2                         = '\x2df1c51e09aecf9cacb7bc98cb1742757f163df7'
ARB_USDC                           = '\xaf88d065e77c8cc2239327c5edb3a432268e5831'
-- Bridge2 returns 0x (absent) on Ethereum(1)/Base(8453)/BNB(56)/Avalanche(43114)/Optimism(10)/Polygon(137).
-- Testnet bridge (Arbitrum Sepolia 421614, outside targets): 0x08cfc1b6b2dcf36a1480b99353a354aa8ac56f89
```

---

## 8. Verification & sources

How every constant was verified (2026-06-09):

- **Event topic0 + function selectors:** recomputed locally as `keccak256(canonical signature)` (and `[0:4]` for selectors) with a local keccak implementation, from the verbatim `Bridge2.sol` / `Signature.sol` source. Tuple types were expanded canonically (`Signature` → `(uint256,uint256,uint8)`, `ValidatorSet` → `(uint64,address[],uint64[])`, etc.).
- **Cross-check against live logs:** `eth_getLogs` on the bridge address over recent Arbitrum blocks (around block 471,650,000) confirmed the computed topic0s for `RequestedWithdrawal` (`0xcc10abf5…`), `FinalizedWithdrawal` (`0xe5c7fe3a…`), `FailedWithdrawal` (`0x686cb4ba…`) and `FailedPermitDeposit` (`0xa2dc875d…`) all appear as real emitted logs. The `Deposit` topic (`0x0ee94a97…`) returned **zero** logs across hundreds of thousands of blocks, confirming it is never emitted — consistent with the source having no `emit Deposit`.
- **Selectors against bytecode:** every selector in §2 was confirmed present in the deployed runtime bytecode via PUSH4 (`63<selector>`) dispatch scan; the speculative `whitelistIndex` getter was **absent** and dropped (no whitelist mapping exists — only `lockers`/`finalizers`).
- **Address existence:** `eth_getCode` on all seven target chains — non-empty (19 394 B) only on Arbitrum One (`0x2Df1c51E…3dF7`); `0x` on Ethereum, Base, BNB, Avalanche, Optimism, Polygon.
- **Proxy classification:** `eth_getStorageAt` on Arbitrum for the EIP-1967 implementation, admin, and beacon slots — **all `0x0`**, confirming `Bridge2` is an immutable non-proxy contract (corroborated by source: no upgrade entrypoint, not Ownable).
- **Live state (`eth_call` on Arbitrum):** `usdcToken()` = `0xaf88…5831` (verified by reading USDC's `symbol()` = `"USDC"`); `epoch()` = 7; `nValidators()` = 4; `totalValidatorPower()` = 4; `disputePeriodSeconds()` = 200; `blockDurationMillis()` = 350; `lockerThreshold()` = 2; `paused()` = false; `hotValidatorSetHash()` / `coldValidatorSetHash()` read as shown in §2.2.

Authoritative sources:
- Canonical contract source — [`hyperliquid-dex/contracts` · `Bridge2.sol`](https://github.com/hyperliquid-dex/contracts/blob/master/Bridge2.sol) and [`Signature.sol`](https://github.com/hyperliquid-dex/contracts/blob/master/Signature.sol)
- Official docs — [Hyperliquid Docs · Bridge2 (API)](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/bridge2) and [Hyperliquid Docs · Bridge (HyperCore)](https://hyperliquid.gitbook.io/hyperliquid-docs/hypercore/bridge)
- Explorer — [Arbiscan · Hyperliquid Deposit Bridge 2](https://arbiscan.io/address/0x2df1c51e09aecf9cacb7bc98cb1742757f163df7)
- Audit — bridge logic audited by Zellic (per official docs)
- Bridge deprecation context — Hyperliquid announcement that the Arbitrum bridge will be retired in favor of natively-minted USDC on HyperEVM/HyperCore.
